import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Items from "./pages/Items";
import Bestiary from "./pages/Bestiary";
import Mechanics from "./pages/Mechanics";
import Campaigns from "./pages/Campaigns";
import Notes from "./pages/Notes";
import ShopsLoot from "./pages/ShopsLoot";
import Initiative from "./pages/Initiative";
import BulkImport from "./pages/BulkImport";

export default function App() {
  return (
    <div style={{ display: "flex", height: "100%" }}>
      <Sidebar />
      <main style={{ flex: 1, overflow: "auto", padding: "24px" }}>
        <Routes>
          <Route path="/" element={<Navigate to="/items" replace />} />
          <Route path="/items" element={<Items />} />
          <Route path="/bestiary" element={<Bestiary />} />
          <Route path="/mechanics" element={<Mechanics />} />
          <Route path="/campaigns" element={<Campaigns />} />
          <Route path="/notes" element={<Notes />} />
          <Route path="/shops" element={<ShopsLoot />} />
          <Route path="/initiative" element={<Initiative />} />
          <Route path="/import" element={<BulkImport />} />
        </Routes>
      </main>
    </div>
  );
}
