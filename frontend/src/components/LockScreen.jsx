import { useCallback, useEffect, useState } from "react";
import { login } from "../api";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

export default function LockScreen({ pinLength, onUnlocked }) {
  const [pin, setPin] = useState("");
  const [message, setMessage] = useState("");
  const [shake, setShake] = useState(false);
  const [busy, setBusy] = useState(false);

  const press = useCallback(
    (key) => {
      if (busy) return;
      setMessage("");
      if (key === "⌫") setPin((p) => p.slice(0, -1));
      else if (key) setPin((p) => (p.length < pinLength ? p + key : p));
    },
    [busy, pinLength]
  );

  // Submit as soon as the last digit goes in, like the phone lock screen.
  useEffect(() => {
    if (pin.length !== pinLength) return;
    setBusy(true);
    login(pin)
      .then(onUnlocked)
      .catch((e) => {
        setMessage(e.message);
        setShake(true);
        setTimeout(() => {
          setShake(false);
          setPin("");
          setBusy(false);
        }, 500);
      });
  }, [pin, pinLength, onUnlocked]);

  // Hardware keyboard works too.
  useEffect(() => {
    function onKeyDown(e) {
      if (/^[0-9]$/.test(e.key)) press(e.key);
      else if (e.key === "Backspace") press("⌫");
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [press]);

  return (
    <div className="lock-screen">
      <h1 className="lock-title">Enter PIN</h1>
      <div className={`lock-dots ${shake ? "lock-shake" : ""}`}>
        {Array.from({ length: pinLength }, (_, i) => (
          <span key={i} className={`lock-dot ${i < pin.length ? "filled" : ""}`} />
        ))}
      </div>
      <p className="lock-message">{message}</p>
      <div className="lock-keypad">
        {KEYS.map((key, i) =>
          key ? (
            <button
              key={i}
              className={`lock-key ${key === "⌫" ? "lock-key-back" : ""}`}
              onClick={() => press(key)}
              aria-label={key === "⌫" ? "Delete" : key}
            >
              {key}
            </button>
          ) : (
            <span key={i} />
          )
        )}
      </div>
    </div>
  );
}
