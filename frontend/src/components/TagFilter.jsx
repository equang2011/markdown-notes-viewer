export default function TagFilter({ tags, active, onChange }) {
  if (tags.length === 0) return null;

  return (
    <div className="tag-filter">
      <button
        className={`tag ${active === null ? "tag-active" : ""}`}
        onClick={() => onChange(null)}
      >
        All
      </button>
      {tags.map(({ tag, count }) => (
        <button
          key={tag}
          className={`tag ${active === tag ? "tag-active" : ""}`}
          onClick={() => onChange(active === tag ? null : tag)}
        >
          {tag} <span className="tag-count">{count}</span>
        </button>
      ))}
    </div>
  );
}
