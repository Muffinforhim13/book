import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Login } from "./pages/Login";
import { OrdersPage } from "./pages/Orders";
import { OrderDetailsPage } from "./pages/OrderDetails";
import { ManagersPage } from "./pages/Managers";
import { ProfilePage } from "./pages/Profile";
import { PhotosPage } from "./pages/Photos";
import { DelayedMessagesPage } from "./pages/DelayedMessages";
import { ContentPage } from "./pages/Content";
import { PricingPage } from "./pages/Pricing";
import { MetricsPage } from "./pages/Metrics";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { Navigation } from "./components/Navigation";

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/admin/orders"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <OrdersPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/orders/:id"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <OrderDetailsPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/photos"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <PhotosPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/delayed-messages"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <DelayedMessagesPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/content"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <ContentPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/metrics"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <MetricsPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/managers"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <ManagersPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/pricing"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <PricingPage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/profile"
          element={
            <ProtectedRoute>
              <div>
                <Navigation />
                <ProfilePage />
              </div>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
};

export default App;
