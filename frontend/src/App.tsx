import { useEffect, useState } from 'react';

function App() {
  const goToApi = () => {
    // This will navigate the browser to the FastAPI /api/ route
    window.location.href = 'http://localhost:8000/api/';
  };

  return (
    <div>
      <h1>Welcome to My App</h1>
      <button onClick={goToApi}>Go to API</button>
    </div>
  );
}

export default App;




