interface Props {
  tag: string;
  onRemove?: () => void;
}

export default function TagBadge({ tag, onRemove }: Props) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: "var(--surface2)", border: "1px solid var(--border)",
      borderRadius: 12, padding: "2px 8px", fontSize: 11,
      color: "var(--text-muted)",
    }}>
      {tag}
      {onRemove && (
        <button
          onClick={onRemove}
          style={{ background: "none", padding: 0, fontSize: 12, color: "var(--text-muted)", lineHeight: 1 }}
        >×</button>
      )}
    </span>
  );
}
