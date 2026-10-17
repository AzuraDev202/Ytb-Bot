export function TableLoading({label = 'Đang đọc dữ liệu…'}: {label?: string}) {
  return <div className="table-loading" role="status" aria-label={label}>
    <div className="loading-label"><span className="loading-dot"/>{label}</div>
    <div className="skeleton-table" aria-hidden="true">{Array.from({length: 4}, (_, row) => <div key={row}>{Array.from({length: 3}, (_, col) => <span key={col}/>)}</div>)}</div>
  </div>;
}
