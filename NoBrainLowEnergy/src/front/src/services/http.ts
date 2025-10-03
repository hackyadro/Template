import axios from "axios";

const http = axios.create({
	baseURL: `http://192.168.137.1:8000/api/v1`
});

export default http;
