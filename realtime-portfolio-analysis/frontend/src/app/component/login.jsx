"use client";
import { useState } from "react";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    //onLogin();
    try {
      const url = `https://rtpa-be.azurewebsites.net/api/users?email_id=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
      // const url = `http://127.0.0.1:8000/api/users?email_id=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;

      const response = await fetch(url, { method: "GET" });
      if (!response.ok) {
        throw new Error("Login failed");
      }
      const data = await response.json();
      // Store response in localStorage
      console.log("Login response:", data);

      onLogin(data);

      localStorage.setItem("user", JSON.stringify(data));
    } catch (error) {
      console.error("Login error:", error);
      // Optionally, show error to user
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-black">
      {/* Logo */}
      <span className="text-2xl font-bold tracking-tight text-slate-100 drop-shadow mb-8">
        EY Prometheus
      </span>
      {/* Title */}
      {/* <h1 className="text-3xl font-bold text-white mb-8">EY Prometheus</h1> */}
      {/* Login Form */}
      <form
        onSubmit={handleSubmit}
        className="bg-gray-900 rounded-xl shadow-lg p-8 flex flex-col gap-4 w-80"
      >
        <input
          type="text"
          placeholder="Username"
          className="p-3 rounded bg-gray-800 text-white border border-gray-700 focus:outline-none"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          type="password"
          placeholder="Password"
          className="p-3 rounded bg-gray-800 text-white border border-gray-700 focus:outline-none"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded p-3 mt-2 transition"
        >
          Login
        </button>
      </form>
    </div>
  );
}
