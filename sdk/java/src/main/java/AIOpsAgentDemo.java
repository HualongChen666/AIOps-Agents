import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class AIOpsAgentDemo {
    public static void main(String[] args) throws Exception {
        String baseUrl = System.getenv().getOrDefault("AIOPS_BASE_URL", "http://localhost:8000");
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();

        // Health check
        HttpRequest health = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/health"))
                .GET()
                .build();
        HttpResponse<String> healthResp = client.send(health, HttpResponse.BodyHandlers.ofString());
        System.out.println("Health: " + healthResp.statusCode() + " " + healthResp.body());

        // AI analyze
        String aiBody = "{"
                + "\"query\": \"CPU usage is high, analyze root cause\","
                + "\"platform\": \"windows\","
                + "\"include_metrics\": true"
                + "}";
        HttpRequest ai = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/ai/analyze"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(aiBody))
                .build();
        HttpResponse<String> aiResp = client.send(ai, HttpResponse.BodyHandlers.ofString());
        System.out.println("AI analyze: " + aiResp.statusCode() + " " + aiResp.body());

        // Alerts
        HttpRequest alerts = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/alerts?limit=5"))
                .GET()
                .build();
        HttpResponse<String> alertsResp = client.send(alerts, HttpResponse.BodyHandlers.ofString());
        System.out.println("Alerts: " + alertsResp.statusCode() + " " + alertsResp.body());
    }
}
