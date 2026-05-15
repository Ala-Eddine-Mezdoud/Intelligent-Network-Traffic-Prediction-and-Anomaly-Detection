import './Layout.css';

export default function Layout({ children }) {
  return (
    <div className="layout-wrapper">
      <div className="background-layer"></div>
      <div className="content-layer">
        {children}
      </div>
    </div>
  );
}