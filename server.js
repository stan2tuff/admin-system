const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// This is your "Database" for now. 
// When you sell this, you'll want to move this to MongoDB.
let currentAnnouncement = "";
const ADMIN_PASSWORD = "stxn123"; 

// Website sends the message here
app.post('/set-announcement', (req, res) => {
    const { message, password } = req.body;

    if (password !== ADMIN_PASSWORD) {
        return res.status(401).send({ error: "Unauthorized" });
    }

    currentAnnouncement = message;
    console.log("New Announcement:", currentAnnouncement);
    res.send({ success: true });
});

// Roblox game checks this
app.get('/get-announcement', (req, res) => {
    res.json({ message: currentAnnouncement });
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
