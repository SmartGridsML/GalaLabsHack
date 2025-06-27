// src/App.tsx

import React, { useState, FormEvent } from 'react';
import './App.css'; 

import { FaHeart, FaGlobe } from 'react-icons/fa';
import { BsPlus, BsArrowUp } from 'react-icons/bs';

// The URL of our Python Flask server
const API_URL = 'http://localhost:5000/send-dm';

function App() {
  const [username, setUsername] = useState(''); 
  // State for the input field
  const [message, setMessage] = useState('');
  // State to track loading status
  const [isLoading, setIsLoading] = useState(false);
  // State to show success/error messages from the server
  const [status, setStatus] = useState('');

  // Function to handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); // Prevent the page from reloading on submit
    if (!message || isLoading) return; // Don't send empty messages or if already loading

    setIsLoading(true);
    setStatus('Sending...');

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          username: username,
          message: message 
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        // If the server returned an error (e.g., 500), throw an error
        throw new Error(data.status || 'An error occurred.');
      }
      
      // On success
      setStatus(data.status);
      setMessage(''); // Clear the input field

    } catch (error) {
      if (error instanceof Error) {
        setStatus(`Error: ${error.message}`);
      } else {
        setStatus('An unknown error occurred.');
      }
    } finally {
      // This will run whether the request succeeded or failed
      setIsLoading(false);
    }
  };


  return (
    <>
      <header className="header">
        <div className="logo">
          <span className="logoIcon"><FaHeart /></span>
          Ripple AI
        </div>
      </header>

      <main className="hero">
        <h1 className="headline">
          Automate your Instagram DMs with AI
        </h1>
        <p className="subheadline">
          Personalized messages at scale
        </p>

        {/* We use a form for better accessibility and event handling */}
        <form className="promptContainer" onSubmit={handleSubmit}>
          {/* THIS IS THE CRITICAL PART */}
          <div className="promptInputArea">
            {/* MAKE SURE ONLY THE INPUT IS HERE */}

            <input
              type="text"
              className="chatInput usernameInput" // Added a new class for styling
              placeholder="Instagram Username..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
            />
            <input
              type="text"
              className="chatInput"
              placeholder="Type your Instagram message here..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="promptControls">
            <button type="submit" className="submitButton" disabled={isLoading}>
              {isLoading ? '...' : <BsArrowUp size={24} />}
            </button>
          </div>
        </form>

        {/* Display the status message from the server */}
        {status && <p className="statusMessage">{status}</p>}
      </main>
    </>
  );
}

export default App;