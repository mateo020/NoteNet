import { IonButton, IonInput, IonItem } from '@ionic/react';
import { useState } from 'react';

const QuestionInput: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');

  const handleSubmit = async () => {
    const response = await fetch('http://your-api-url/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });
    
    const data = await response.json();
    setAnswer(data.answer);
  };

  return (
    <div>
      <IonItem>
        <IonInput
          value={question}
          onIonChange={(e) => setQuestion(e.detail.value!)}
          placeholder="Enter your question"
        />
      </IonItem>
      <IonButton expand="block" onClick={handleSubmit}>
        Ask
      </IonButton>
      
      {answer && (
        <div className="answer-section">
          <h3>Answer:</h3>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
};