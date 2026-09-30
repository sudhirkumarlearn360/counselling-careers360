import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { Providers, makeQueryClient } from "./app/providers";
import { makeRouter } from "./app/router";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Providers client={makeQueryClient()}>
      <RouterProvider router={makeRouter()} future={{ v7_startTransition: true }} />
    </Providers>
  </React.StrictMode>,
);
