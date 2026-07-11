import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "./store";
import { fetchProfileThunk } from "./store/authSlice";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";

const AppInit: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      store.dispatch(fetchProfileThunk());
    }
  }, []);
  return <>{children}</>;
};

const App: React.FC = () => (
  <Provider store={store}>
    <ErrorBoundary>
      <AppInit>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AppInit>
    </ErrorBoundary>
  </Provider>
);

export default App;
