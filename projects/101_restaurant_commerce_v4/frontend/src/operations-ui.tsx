import { useRef, useState } from "react";
import { ApiError } from "./ui";

export async function operationApi<T>(
  url: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(url, {
    credentials: "same-origin",
    signal: AbortSignal.timeout(20000),
    ...init,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event("session-expired"));
    const error = new ApiError(response.status);
    if (response.status < 500 && typeof data?.detail === "string")
      error.message = data.detail.slice(0, 500);
    throw error;
  }
  return data;
}

// One reviewed command at a time. Mutations are never retried automatically.
export function useOperation(csrf: string) {
  const running = useRef(false);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [message, setMessage] = useState("");
  async function perform<T>(
    url: string,
    body?: unknown,
    method = "POST",
  ): Promise<T | undefined> {
    if (running.current || uncertain) return;
    running.current = true;
    setBusy(true);
    setMessage("");
    try {
      return await operationApi<T>(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-101-CSRF": csrf,
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch (error) {
      if (error instanceof ApiError && error.status < 500)
        setMessage(error.message);
      else {
        setUncertain(true);
        setMessage(
          "No recibimos confirmación. Comprueba el estado antes de hacer otra acción.",
        );
      }
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  return {
    perform,
    busy,
    uncertain,
    message,
    setMessage,
    checked: () => {
      setUncertain(false);
      setMessage("Estado actualizado. Revisa los datos antes de continuar.");
    },
  };
}

export function OperationNotice({ message }: { message: string }) {
  return message ? (
    <p className="operation-notice" role="status">
      {message}
    </p>
  ) : null;
}
