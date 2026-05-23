import os
import re
import json
import time
import uuid
import yaml
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.RAG_engine import build_vector_database, create_retriever_chain

CLAUDE_INBOX_DIR = os.path.join(os.path.dirname(__file__), "_claude")
os.makedirs(CLAUDE_INBOX_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _has_valid_hf_token() -> bool:
    tok = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
    return tok.startswith("hf_") and "REPLACE_ME" not in tok and len(tok) > 12


def _has_anthropic_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return key.startswith("sk-ant-") and "REPLACE_ME" not in key and len(key) > 20


def _claude_chat_enabled() -> bool:
    """Filesystem-channel mode (legacy test harness): off by default. Set CLAUDE_CHAT_MODE=1 to enable."""
    return os.getenv("CLAUDE_CHAT_MODE", "0") == "1"


print("Initializing Vector Database...")
db = build_vector_database()
if db:
    print(f"Vector DB ready ({db._collection.count()} chunks)")
else:
    print("Warning: Vector database could not be built.")

matcher = None
if _claude_chat_enabled():
    print(f"CLAUDE-CHAT MODE: inbox at {CLAUDE_INBOX_DIR}. "
          "Drop a response.json there to answer queries.")
elif db and (_has_anthropic_key() or _has_valid_hf_token()):
    print("Initializing Retriever Chain...")
    matcher = create_retriever_chain(db)
else:
    print("DEMO MODE: no LLM available. /api/match uses retrieval-only fallback.")


class MatchRequest(BaseModel):
    query: str


_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_COLOR_THEMES = ["purple", "green", "blue"]


def _parse_front_matter(text: str) -> Dict[str, Any]:
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return "NA"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def _seniority_label(seniority: Any) -> str:
    if not seniority:
        return "Candidate"
    s = str(seniority).strip().lower()
    return {
        "intern": "Intern",
        "junior": "Junior",
        "mid": "Mid-level",
        "senior": "Senior",
        "founder": "Founder",
    }.get(s, s.title())


def _role_string(meta: Dict[str, Any]) -> str:
    seniority = _seniority_label(meta.get("seniority"))
    role = meta.get("current_role_title") or meta.get("last_role_title") or "Engineer"
    city = meta.get("location_city") or meta.get("location_secondary") or ""
    role_part = f"{seniority} {role}".strip()
    return f"{role_part}{' · ' + city if city else ''}"


def _tags_from_meta(meta: Dict[str, Any], max_tags: int = 3) -> List[str]:
    techs = meta.get("technologies") or []
    out: List[str] = []
    for t in techs:
        if isinstance(t, dict):
            name = t.get("tech")
        else:
            name = t
        if name:
            out.append(str(name))
        if len(out) >= max_tags:
            break
    if not out:
        return ["—", "—", "—"]
    while len(out) < max_tags:
        out.append("—")
    return out


def _languages_from_meta(meta: Dict[str, Any]) -> str:
    langs = meta.get("languages") or []
    out: List[str] = []
    for l in langs:
        if isinstance(l, dict):
            code = l.get("lang")
        else:
            code = l
        if code:
            out.append(str(code).upper())
    return " · ".join(out[:3]) if out else "—"


def _retrieval_fallback(query: str, k: int = 3) -> List[Dict[str, Any]]:
    if not db:
        return []
    results = db.similarity_search_with_score(query, k=k * 4)

    seen: Dict[str, Dict[str, Any]] = {}
    for doc, score in results:
        source = (doc.metadata.get("source") or "").replace("\\", "/")
        folder = source.split("/candidates/")[-1].split("/")[0] if "/candidates/" in source else source
        if not folder or folder in seen:
            continue
        seen[folder] = {"doc": doc, "score": float(score), "folder": folder}
        if len(seen) >= k:
            break

    if not seen:
        return []

    candidates: List[Dict[str, Any]] = []
    ranked = sorted(seen.values(), key=lambda x: x["score"])
    max_dist = max((c["score"] for c in ranked), default=1.0) or 1.0

    for i, c in enumerate(ranked):
        meta = _parse_front_matter(c["doc"].page_content)
        if not meta:
            src = (c["doc"].metadata.get("source") or "").replace("\\", "/")
            if src and os.path.isfile(src):
                try:
                    with open(src, "r", encoding="utf-8") as f:
                        meta = _parse_front_matter(f.read())
                except OSError:
                    meta = {}
        name = meta.get("name") or meta.get("full_name") or c["folder"].rsplit("-", 1)[0].replace("-", " ").title()
        match_pct = max(40, min(98, int(round(100 - (c["score"] / (max_dist + 0.5)) * 60))))
        candidates.append({
            "initials": _initials(name),
            "name": name,
            "role": _role_string(meta),
            "matchScore": match_pct,
            "matchRank": f"#{i + 1} match",
            "skillsScore": max(40, match_pct - 5),
            "expScore": max(30, match_pct - 15),
            "locationScore": max(40, match_pct - 10),
            "tags": _tags_from_meta(meta),
            "langs": _languages_from_meta(meta),
            "colorTheme": _COLOR_THEMES[i % len(_COLOR_THEMES)],
        })
    return candidates


def _retrieve_context_docs(query: str, k: int = 5) -> List[Dict[str, Any]]:
    if not db:
        return []
    out: List[Dict[str, Any]] = []
    for doc, score in db.similarity_search_with_score(query, k=k):
        src = (doc.metadata.get("source") or "").replace("\\", "/")
        folder = src.split("/candidates/")[-1].split("/")[0] if "/candidates/" in src else src
        meta = _parse_front_matter(doc.page_content)
        if not meta and src and os.path.isfile(src):
            try:
                with open(src, "r", encoding="utf-8") as f:
                    meta = _parse_front_matter(f.read())
            except OSError:
                meta = {}
        out.append({
            "folder": folder,
            "distance": float(score),
            "page_content": doc.page_content,
            "frontmatter": meta,
            "source": src,
        })
    return out


def _ask_claude_via_filesystem(query: str, timeout_s: float = 300.0) -> Optional[List[Dict[str, Any]]]:
    """Write the request to disk, poll for a response file written by a human Claude."""
    req_id = uuid.uuid4().hex[:8]
    pending_path = os.path.join(CLAUDE_INBOX_DIR, "pending.json")
    response_path = os.path.join(CLAUDE_INBOX_DIR, "response.json")

    if os.path.exists(response_path):
        try:
            os.remove(response_path)
        except OSError:
            pass

    context = _retrieve_context_docs(query, k=5)
    payload = {
        "id": req_id,
        "ts": time.time(),
        "query": query,
        "context": context,
        "schema": {
            "candidates": "List of up to 3 objects with keys: initials, name, role, "
                          "matchScore (0-100), matchRank (e.g. '#1 match'), skillsScore, "
                          "expScore, locationScore, tags (3 strings), langs, "
                          "colorTheme ('purple'|'green'|'blue')",
        },
    }
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print(f"[claude-chat] Waiting for Claude response (req {req_id}, query={query!r})...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if os.path.exists(response_path):
            try:
                with open(response_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                resp_id = data.get("id")
                if resp_id and resp_id != req_id:
                    time.sleep(0.5)
                    continue
                candidates = data.get("candidates", [])
                print(f"[claude-chat] Got response for req {req_id} ({len(candidates)} candidates)")
                try:
                    os.remove(response_path)
                    os.remove(pending_path)
                except OSError:
                    pass
                return candidates
            except (OSError, json.JSONDecodeError):
                time.sleep(0.5)
                continue
        time.sleep(0.5)

    print(f"[claude-chat] Timed out waiting for Claude response (req {req_id})")
    try:
        os.remove(pending_path)
    except OSError:
        pass
    return None


@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    if _claude_chat_enabled() and db:
        claude_resp = _ask_claude_via_filesystem(request.query)
        if claude_resp is not None:
            return claude_resp
        print("[claude-chat] Falling back to retrieval-only")
        return _retrieval_fallback(request.query)

    if matcher:
        try:
            response = matcher.invoke({"input": request.query})
            answer = (response.get("answer") or "").strip()
            if answer.startswith("```json"):
                answer = answer[7:]
            elif answer.startswith("```"):
                answer = answer[3:]
            if answer.endswith("```"):
                answer = answer[:-3]
            answer = answer.strip()
            if not answer or answer == "[]":
                return []
            try:
                return json.loads(answer)
            except json.JSONDecodeError:
                print(f"LLM returned non-JSON; falling back to retrieval. Raw: {answer[:200]}")
                return _retrieval_fallback(request.query)
        except Exception as e:
            print(f"LLM error, falling back to retrieval: {e}")
            return _retrieval_fallback(request.query)

    return _retrieval_fallback(request.query)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
