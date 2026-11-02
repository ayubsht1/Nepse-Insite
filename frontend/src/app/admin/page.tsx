import App from '../../App';

export default function AdminPage() {
  return <App initialTab="admin-panel" requiredRole="admin" />;
}
