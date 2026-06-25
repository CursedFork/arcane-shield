import { NavLink } from "react-router-dom";

const links = [
  { to: "/items",      label: "Magic Items",  icon: "✦" },
  { to: "/bestiary",   label: "Bestiary",     icon: "☠" },
  { to: "/mechanics",  label: "Mechanics",    icon: "⚙" },
  { to: "/campaigns",  label: "Campaigns",    icon: "📖" },
  { to: "/notes",      label: "Notes",        icon: "✎" },
  { to: "/shops",      label: "Shops & Loot", icon: "⚖" },
  { to: "/initiative", label: "Initiative",   icon: "⚔" },
  { to: "/import",    label: "Bulk Import",  icon: "⬆" },
];

export default function Sidebar() {
  return (
    <nav style={{
      width: "var(--sidebar-w)",
      minWidth: "var(--sidebar-w)",
      background: "var(--surface)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      padding: "16px 0",
    }}>
      <div style={{ padding: "0 16px 20px", fontWeight: 700, fontSize: 15, color: "var(--accent)", letterSpacing: 1 }}>
        ⚔ ARCANE SHIELD
      </div>
      {links.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => ({
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "9px 16px",
            color: isActive ? "var(--text)" : "var(--text-muted)",
            background: isActive ? "var(--surface2)" : "transparent",
            borderLeft: isActive ? "2px solid var(--accent)" : "2px solid transparent",
            fontSize: 13,
            transition: "all 0.1s",
          })}
        >
          <span>{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
