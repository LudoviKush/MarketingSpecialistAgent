import React, { useState, useRef, useEffect } from 'react';
import {
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import { CloudUpload, Send } from "@mui/icons-material";
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<{ text: string; sender: string }[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [platform, setPlatform] = useState('linkedin');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file first!');
      return;
    }

    setIsLoading(true);
    const formData = new FormData();
    formData.append('video', file);
    formData.append('platform', platform);

    try {
      const response = await axios.post('http://127.0.0.1:5000/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setMessages([
        ...messages,
        { text: 'Video uploaded and analyzed', sender: 'user' },
        { text: response.data.analysis, sender: 'bot' }
      ]);
    } catch (error) {
      console.error('Error uploading file:', error);
      setMessages([...messages, { text: 'Error uploading and analyzing video', sender: 'bot' }]);
    }
    setIsLoading(false);
  };

  const handleSendMessage = async () => {
    if (inputMessage.trim() !== '') {
      setMessages([...messages, { text: inputMessage, sender: 'user' }]);
      setInputMessage('');
      setIsLoading(true);

      try {
        const response = await axios.post('http://127.0.0.1:5000/chat', { message: inputMessage });
        setMessages(prevMessages => [...prevMessages, { text: response.data.reply, sender: 'bot' }]);
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages(prevMessages => [...prevMessages, { text: 'Error: Unable to get response', sender: 'bot' }]);
      }

      setIsLoading(false);
    }
  };

  return (
    <Box className="app-container">
      <Box className="chat-paper">
        <Typography variant="h4" gutterBottom className="app-title">
          Marketing Video Analysis Agent
        </Typography>
        <Box className="upload-area">
          <FormControl variant="outlined" className="platform-select">
            <InputLabel>Platform</InputLabel>
            <Select
              value={platform}
              onChange={(e) => setPlatform(e.target.value as string)}
              label="Platform"
            >
              <MenuItem value="tiktok">TikTok</MenuItem>
              <MenuItem value="linkedin">LinkedIn</MenuItem>
            </Select>
          </FormControl>
          <input
            accept="video/*"
            style={{ display: 'none' }}
            id="raised-button-file"
            type="file"
            onChange={handleFileChange}
            ref={fileInputRef}
          />
          <label htmlFor="raised-button-file">
            <Button
              variant="contained"
              color="primary"
              component="span"
              startIcon={<CloudUpload />}
              className="upload-button"
            >
              SELECT VIDEO
            </Button>
          </label>
          {file && (
            <Typography variant="body2" className="file-name">
              Selected file: {file.name}
            </Typography>
          )}
          <Button
            variant="contained"
            color="secondary"
            onClick={handleUpload}
            disabled={!file || isLoading}
            className="analyze-button"
          >
            UPLOAD AND ANALYZE
          </Button>
          {isLoading && <CircularProgress className="loading-indicator" />}
        </Box>
        <Box className="chat-area">
          <List>
            {messages.map((message, index) => (
              <ListItem key={index} className={`chat-message ${message.sender}`}>
                <ListItemText
                  primary={message.sender === 'user' ? 'You' : 'Bot'}
                  secondary={
                    <ReactMarkdown>
                      {message.text}
                    </ReactMarkdown>
                  }
                />
              </ListItem>
            ))}
            <div ref={chatEndRef} />
          </List>
        </Box>
        <Box className="input-area">
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Type a message..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            className="message-input"
          />
          <Button
            variant="contained"
            color="primary"
            endIcon={<Send />}
            onClick={handleSendMessage}
            className="send-button"
          >
            SEND
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

export default App;