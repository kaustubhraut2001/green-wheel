import { useEffect, useRef, useCallback } from "react";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "../store";
import { updateWalletBalance, prependTransaction } from "../store/walletSlice";

interface SSEWalletEvent {
  event_type: string;
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
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    const url = `/api/v1/events/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener("wallet_update", (e: MessageEvent) => {
      try {
        const data: SSEWalletEvent = JSON.parse(e.data);

        // 1. Update the wallet card balance instantly
        dispatch(updateWalletBalance({
          walletId: data.wallet_id,
          newBalance: data.new_balance,
        }));

        // 2. Prepend the new transaction row to the table instantly
        dispatch(prependTransaction({
          wallet_id: data.wallet_id,
          transaction_type: data.transaction_type,
          amount: data.amount,
          currency: data.currency,
          new_balance: data.new_balance,
          event_type: data.event_type,
          note: data.note ?? null,
        }));

      } catch (err) {
        console.error("[SSE] parse error", err);
      }
    });

    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Reconnect after 4 s
      timerRef.current = setTimeout(connect, 4000);
    };
  }, [dispatch]);

  useEffect(() => {
    connect();
    return () => {
      timerRef.current && clearTimeout(timerRef.current);
      esRef.current?.close();
    };
  }, [connect]);
}
