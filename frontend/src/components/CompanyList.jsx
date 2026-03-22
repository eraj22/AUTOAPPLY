export default function CompanyList({ companies = [] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {companies.map((company) => (
        <div key={company.id} className="card">
          <h3 className="font-bold text-lg">{company.name}</h3>
          <p className="text-gray-600">{company.careers_url}</p>
        </div>
      ))}
    </div>
  )
}
