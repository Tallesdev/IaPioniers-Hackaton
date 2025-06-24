using System.Net.Http;
using System.Threading.Tasks;

namespace IaPioniers.Services
{
    public class IaPioniersApiService
    {
        private readonly HttpClient _httpClient;

        public IaPioniersApiService(HttpClient httpClient)
        {
            _httpClient = httpClient;
        }

        // Exemplo de método que consulta a API Python
        public async Task<string> GetSaudacaoAsync()
        {
            var response = await _httpClient.GetAsync("/saudacao"); // substitua por um endpoint real da sua API Python
            response.EnsureSuccessStatusCode();

            return await response.Content.ReadAsStringAsync();
        }
    }
}
