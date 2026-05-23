import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import './index.css';

export interface Candidate {
  initials: string;
  name: string;
  role: string;
  matchScore: number;
  matchRank: string;
  skillsScore: number;
  expScore: number;
  locationScore: number;
  tags: string[];
  langs: string;
  colorTheme: 'purple' | 'green' | 'blue';
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  candidates?: Candidate[];
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: 'Salut! Sunt asistentul tău CVision. Introdu specificațiile jobului sau profilul căutat pentru a scana baza de date Obsidian și a genera shortlist-ul.'
    }
  ]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleHRQuery = async (queryText: string) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: queryText
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText }),
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();

      // SAFETY NET: Ne asigurăm că datele sunt mereu un array pentru a nu bloca .map()
      let candidatesArray: Candidate[] = [];
      if (Array.isArray(data)) {
        candidatesArray = data;
      } else if (data && typeof data === 'object') {
        // Dacă LLM-ul a returnat doar un obiect în loc de o listă cu un obiect
        candidatesArray = [data as Candidate];
      }

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: candidatesArray.length > 0
          ? `Am analizat profilurile din Obsidian. Iată topul candidaților care corespund cerințelor tale:`
          : `Nu am găsit candidați în baza de date care să se potrivească perfect cu descrierea oferită. Încearcă să schimbi tehnologiile sau locația.`,
        candidates: candidatesArray
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      console.error("Eroare conexiune backend:", error);
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: 'Eroare: Nu am putut comunica cu motorul RAG. Verifică dacă backend-ul Python rulează pe portul 8000.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <ChatArea messages={messages} onSendMessage={handleHRQuery} isLoading={isLoading} />
      </main>
    </div>
  );
}

export default App;