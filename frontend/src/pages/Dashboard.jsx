import { useQuery } from '@tanstack/react-query'
import { companiesAPI } from '../api/client'

export default function Dashboard() {
  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesAPI.list().then(res => res.data),
    refetchInterval: 5000,
  })

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <button className="btn-primary">
          Add Company
        </button>
      </div>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {companies.map((company) => (
            <div key={company.id} className="card hover:shadow-lg transition">
              <h3 className="text-lg font-bold mb-2">{company.name}</h3>
              <p className="text-gray-600 text-sm mb-4">{company.careers_url}</p>
              <div className="flex gap-2">
                <button className="text-blue-600 text-sm hover:underline">Edit</button>
                <button className="text-red-600 text-sm hover:underline">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {companies.length === 0 && !isLoading && (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No companies added yet</p>
          <button className="btn-primary">Add Your First Company</button>
        </div>
      )}
    </div>
  )
}
