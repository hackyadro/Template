require('dotenv').config();
const port = process.env.PORT;

const path = require('path');
const express = require('express');
const app = express();

app.get('/', (req, res) => {
	res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(port, () => {
	console.log(`Starting server on ${port}`);
});
