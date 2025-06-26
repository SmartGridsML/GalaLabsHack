import React from 'react';
import './App.css';

// We're using the popular 'react-icons' library for the icons.
// You can install it with: npm install react-icons
import { FaHeart, FaGlobe } from 'react-icons/fa';
import { BsPlus, BsArrowUp } from 'react-icons/bs';
import { FiLink, FiMessageSquare, FiDatabase, FiHome } from 'react-icons/fi';


const LovablePage = () => {
  return (
    <div className="lovablePage">
      <header className="header">
        <div className="logo">
          <span className="logoIcon"><FaHeart /></span>
          Lovable
        </div>
        <nav className="navLinks">
          <a href="#">Community</a>
          <a href="#">Enterprise</a>
          <a href="#">Learn</a>
          <a href="#">Shipped</a>
        </nav>
        <div className="authButtons">
          <button className="loginButton">Log in</button>
          <button className="getStartedButton">Get started</button>
        </div>
      </header>

      <main className="hero">
        <h1 className="headline">
          Build something <span className="heartIcon"><FaHeart /></span> <strong>Lovable</strong>
        </h1>
        <p className="subheadline">
          Create apps and websites by chatting with AI
        </p>

        <div className="promptContainer">
          <div className="promptInputArea">
            <p>Ask Lovable to create an internal tool that.</p>
          </div>
          <div className="promptControls">
            <div className="promptActions">
              <button className="promptButton plusButton"><BsPlus size={24} /></button>
              <button className="promptButton publicButton">
                <FaGlobe />
                <span>Public</span>
              </button>
            </div>
            <button className="submitButton">
              <BsArrowUp size={24} />
            </button>
          </div>
        </div>

        <div className="suggestions">
          <button className="suggestionButton">
            <FiLink /> E-commerce store
          </button>
          <button className="suggestionButton">
            <FiMessageSquare /> Social media feed
          </button>
          <button className="suggestionButton">
            <FiDatabase /> Hacker News top 100
          </button>
          <button className="suggestionButton">
            <FiHome /> Real estate listings
          </button>
        </div>
      </main>
    </div>
  );
};

export default LovablePage;