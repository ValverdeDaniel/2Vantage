/* The carrier's category legend above Florida Blue's Section IV (G36): a static table of category names. */
export default function Legend({ rows }) {
  if (!rows?.length) return null;
  return (
    <table className="bnf-q-legend">
      <tbody>
        {rows.map((row) => (
          <tr key={row.join('|')}>
            {row.map((cell) => (
              <td key={cell}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
