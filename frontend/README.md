# ExamShield Frontend

React + Vite + Tailwind CSS prototype for the ExamShield Review II demonstration.

## Features

- Drag-and-drop PDF upload
- PDF validation and 10 MB size limit
- Verification progress animation
- Integrity / hash / blockchain / AI verification status cards
- Authentic result screen
- Responsive dark cybersecurity UI
- Ready to connect to the Flask backend

## Run

Install Node.js (LTS), then:

```bash
npm install
npm run dev
```

Open the local Vite URL shown in the terminal.

## Connect the Flask backend

The current `verify()` function is a frontend-only prototype. Replace it with a `fetch()` request to your Flask endpoint, for example:

```js
const formData = new FormData();
formData.append("file", file);

const response = await fetch("http://127.0.0.1:5000/verify", {
  method: "POST",
  body: formData,
});

const result = await response.json();
```

Then map the backend response into the result card.

Expected backend response can look like:

```json
{
  "status": "AUTHENTIC",
  "hash_match": true,
  "blockchain_verified": true,
  "integrity": true,
  "document_hash": "abc123...",
  "timestamp": "2026-09-22T21:30:00",
  "message": "Document verified successfully"
}
```

Do not claim a document is authentic in production unless the backend actually performs the required checks. The included success result is intentionally a UI demo state.
