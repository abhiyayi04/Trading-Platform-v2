export default function ProfilePage({ user, onLogout }) {
  const funds = Number(user?.funds ?? 0).toFixed(2);

  return (
    <div className="page">
        <div className="panel">
      <div className="cardHeader">
        <h1 className="title">Profile</h1>
        <button className="btn danger" onClick={onLogout}>
          Logout
        </button>
      </div>

      <div className="grid2">
        <div className="kv">
          <div className="k">Username</div>
          <div className="v">{user?.name}</div>
        </div>

        <div className="kv">
          <div className="k">Email</div>
          <div className="v">{user?.email}</div>
        </div>

        <div className="kv">
          <div className="k">Role</div>
          <div className="v">{user?.role}</div>
        </div>

        <div className="kv">
          <div className="k">Funds</div>
          <div className="v">${funds}</div>
        </div>
      </div>
      </div>
    </div>
  );
}