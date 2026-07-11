/**
 * useWalletSSE — React hook for Server-Sent Events wallet updates.
 *
 * Connects to /api/v1/events/stream and listens for wallet_update events.
 * On receiving an event, updates Redux state directly so the UI reflects
 * the new balance instantly — no polling, no manual refresh needed.
 *
 * Reconnects automatically if the connection drops (built into EventSource).
 */
import { useEffect, useRef } from "react";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "../store";
import {
  updateWalletBalance,
  addLiveTransaction,
} from "../store/walletSlice";

interface WalletEvent {
  event_type: string;       // "credit" | "debit" | "transfer_sent" | "transfer_received"
  wallet_id: string;
  currency: string;
  new_balance: string;
  amount: string;
  transaction_type: string;
  reference: string | null;
  note: string | null;
  exchange_rate: string | null;
}

export function useWalletSSE() {
  const dispatch = useDispatch<AppDispatch>();
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    function connect() {
      // Close any existing connection first
      if (esRef.current) {
        esRef.current.close();
      }

      const url = `/api/v1/events/stream?token=${encodeURIComponent(token!)}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.addEventListener("connected", () => {
        console.log("[SSE] Connected to wallet event stream");
      });

      es.addEventListener("wallet_update", (e: MessageEvent) => {
        try {
          const data: WalletEvent = JSON.parse(e.data);
          console.log("[SSE] wallet_update received:", data);

          // Update wallet balance in Redux store immediately
          dispatch(updateWalletBalance({
            walletId: data.wallet_id,
            newBalance: data.new_balance,
          }));

          // Add transaction to the live feed
          dispatch(addLiveTransaction({
            wallet_id: data.wallet_id,
            transaction_type: data.transaction_type,
            amount: data.amount,
            currency: data.currency,
            event_type: data.event_type,
            note: data.note,
          }));

        } catch (err) {
          console.error("[SSE] Failed to parse event:", err);
        }
      });

      es.onerror = (err) => {
        console.warn("[SSE] Connection error, reconnecting in 3s...", err);
        es.close();
        esRef.current = null;
        // Reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [dispatch]);
}
