import ReactMarkdown from "react-markdown";

interface Props {
  content: string;
}

export default function MarkdownView({ content }: Props) {
  return (
    <div style={{
      lineHeight: 1.7, fontSize: 13, color: "var(--text)",
      overflowY: "auto", padding: "4px 0",
    }}
      className="md-view"
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
