import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyDuuMptjSohD7x9gTG5XB9B31I_o4tVrTw",
  authDomain: "swave-d8549.firebaseapp.com",
  projectId: "swave-d8549",
  storageBucket: "swave-d8549.firebasestorage.app",
  messagingSenderId: "873979695049",
  appId: "1:873979695049:web:928e2c47461153fe266218",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export default app;

