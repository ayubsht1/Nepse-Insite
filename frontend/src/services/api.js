import axios from "axios";
import { clientEnv } from "@/config/env";

export const api = axios.create({
  baseURL: clientEnv.apiUrl,
  headers: {
    "Content-Type": "application/json",
  },
});
