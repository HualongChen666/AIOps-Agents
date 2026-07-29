package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

func main() {
	baseURL := os.Getenv("AIOPS_BASE_URL")
	if baseURL == "" {
		baseURL = "http://localhost:8000"
	}
	client := &http.Client{Timeout: 30 * time.Second}

	// Health check
	healthResp, err := client.Get(baseURL + "/health")
	if err != nil {
		panic(err)
	}
	defer healthResp.Body.Close()
	body, _ := io.ReadAll(healthResp.Body)
	fmt.Printf("Health: %d %s\n", healthResp.StatusCode, string(body))

	// AI analyze
	payload, _ := json.Marshal(map[string]interface{}{
		"query":           "CPU usage is high, analyze root cause",
		"platform":        "windows",
		"include_metrics": true,
	})
	resp, err := client.Post(baseURL+"/api/ai/analyze", "application/json", bytes.NewBuffer(payload))
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	body, _ = io.ReadAll(resp.Body)
	fmt.Printf("AI analyze: %d %s\n", resp.StatusCode, string(body))

	// Alerts
	alertsResp, err := client.Get(baseURL + "/api/alerts?limit=5")
	if err != nil {
		panic(err)
	}
	defer alertsResp.Body.Close()
	body, _ = io.ReadAll(alertsResp.Body)
	fmt.Printf("Alerts: %d %s\n", alertsResp.StatusCode, string(body))
}
