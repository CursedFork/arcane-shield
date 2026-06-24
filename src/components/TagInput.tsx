import { useState, KeyboardEvent } from "react";
import TagBadge from "./TagBadge";

interface Props {
  value: string[];
  onChange: (tags: string[]) => void;
}

export default function TagInput({ value, onChange }: Props) {
  const [input, setInput] = useState("");

  function add() {
    const tag = input.trim().toLowerCase().replace(/\s+/g, "-");
    if (tag && !value.includes(tag)) {
      onChange([...value, tag]);
    }
    setInput("");
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); }
    if (e.key === "Backspace" && input === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  return (
    <div style={{
      display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center",
      background: "var(--surface2)", border: "1px solid var(--border)",
      borderRadius: 4, padding: "4px 8px", minHeight: 34,
    }}>
      {value.map((t) => (
        <TagBadge key={t} tag={t} onRemove={() => onChange(value.filter((x) => x !== t))} />
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKey}
        onBlur={add}
        placeholder={value.length === 0 ? "add tags…" : ""}
        style={{
          border: "none", background: "transparent", outline: "none",
          padding: 0, fontSize: 13, color: "var(--text)", minWidth: 80, flex: 1,
        }}
      />
    </div>
  );
}
