import React from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';

const App: React.FC = () => {
  return (
    <div className="app-container">
      <Sidebar />
      <ChatArea />
    </div>
  );
};

export default App;
