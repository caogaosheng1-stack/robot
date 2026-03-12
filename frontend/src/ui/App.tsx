import React, { useEffect, useMemo, useRef, useState } from "react";

type Snapshot = {
  status: string;
  stats: Record<string, unknown>;
  items: Array<any>;
  robots: Array<any>;
  bins: Array<any>;
  time_data: { simulation_time: number; fps: number; frames: number };
  messages: string[];
  timestamp: string;
};

function useSimulationWs() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/sim`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === "snapshot") {
          setSnapshot(msg.data);
        }
      } catch {
        // ignore
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  return {
    connected,
    snapshot,
    send: (payload: any) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify(payload));
    },
  };
}

export function App() {
  const { connected, snapshot, send } = useSimulationWs();
  const status = snapshot?.status ?? "idle";
  const time = snapshot?.time_data?.simulation_time ?? 0;
  const fps = snapshot?.time_data?.fps ?? 0;
  const frames = snapshot?.time_data?.frames ?? 0;

  const stats = useMemo(() => snapshot?.stats ?? {}, [snapshot]);
  const bins = snapshot?.bins ?? [];
  const robots = snapshot?.robots ?? [];
  const items = snapshot?.items ?? [];

  return (
    <div style={{ fontFamily: "system-ui, Segoe UI, sans-serif", padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <h2 style={{ margin: 0 }}>机器人智能分拣系统</h2>
      <div style={{ marginTop: 8, color: "#555" }}>
        WS: <b>{connected ? "connected" : "disconnected"}</b> · 状态: <b>{status}</b>
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
        <button onClick={() => send({ type: "start", duration: 30 })} disabled={!connected}>
          启动（30s）
        </button>
        <button onClick={() => send({ type: "stop" })} disabled={!connected}>
          停止
        </button>
        <div style={{ marginLeft: "auto", color: "#666" }}>
          t={time.toFixed(2)}s · fps={fps.toFixed(1)} · frames={frames}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
        <Card title="统计">
          <KV label="total_items_processed" value={String((stats as any).total_items_processed ?? "-")} />
          <KV label="items_in_environment" value={String((stats as any).items_in_environment ?? "-")} />
          <KV label="accuracy_rate" value={String((stats as any).accuracy_rate ?? "-")} />
          <KV label="fps" value={String((stats as any).fps ?? "-")} />
        </Card>

        <Card title="分拣箱">
          {bins.length === 0 ? <div style={{ color: "#777" }}>暂无</div> : bins.map((b) => <div key={b.id}>箱 {b.id}: {b.current_count}/{b.capacity} ({b.fill_rate}%)</div>)}
        </Card>

        <Card title="机械臂">
          {robots.length === 0 ? <div style={{ color: "#777" }}>暂无</div> : robots.map((r) => <div key={r.id}>机械臂 {r.id}: {r.state} · 电量 {Number(r.battery).toFixed(1)}%</div>)}
        </Card>

        <Card title="物品（前 20）">
          {items.length === 0 ? <div style={{ color: "#777" }}>暂无</div> : items.slice(0, 20).map((it) => <div key={it.id}>#{it.id} {it.color}/{it.size} ({Math.round(it.position.x)},{Math.round(it.position.y)},{Math.round(it.position.z)})</div>)}
        </Card>

        <div style={{ gridColumn: "1 / -1" }}>
          <Card title="消息">
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: "#333" }}>
              {(snapshot?.messages ?? []).join("\n") || "（空）"}
            </pre>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 12, background: "#fff" }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
      <div style={{ display: "grid", gap: 6 }}>{children}</div>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
      <span style={{ color: "#666" }}>{label}</span>
      <b>{value}</b>
    </div>
  );
}

