import { Link } from "react-router-dom";
import { Empty } from "../components/ui";

export function NotFound() {
  return (
    <div className="panel">
      <Empty title="Page not found">
        <h1 className="skip-link">Page not found</h1>
        Nothing lives at this address. <Link to="/queue">Go to the review queue</Link>.
      </Empty>
    </div>
  );
}
