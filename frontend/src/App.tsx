import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import pkg from "../package.json";
import Home from "./pages/Home";
import Inbox from "./pages/Inbox";
import Recipes from "./pages/Recipes";
import RecipeDetail from "./pages/RecipeDetail";
import TagsPage from "./pages/Tags";
import Settings from "./pages/Settings";

export default function App() {
  const { pathname } = useLocation();
  const isHome = pathname === "/";

  return (
    <div className={["app-shell", isHome ? "app-shell--home" : ""].filter(Boolean).join(" ")}>
      {!isHome && (
        <nav className="sidebar">
          <div className="sidebar-brand">
            <NavLink to="/" className="sidebar-brand-link">
              <h1>Kitchen Ledger</h1>
            </NavLink>
            <p className="sidebar-version">{pkg.version}</p>
          </div>
          <NavLink to="/inbox" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            Inbox
          </NavLink>
          <NavLink to="/recipes" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            Recipes
          </NavLink>
          <NavLink to="/tags" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            Tags
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            Settings
          </NavLink>
        </nav>
      )}
      <main className="main">
        <div className="main-foreground">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/recipes" element={<Recipes />} />
            <Route path="/recipes/:id" element={<RecipeDetail />} />
            <Route path="/tags" element={<TagsPage />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
