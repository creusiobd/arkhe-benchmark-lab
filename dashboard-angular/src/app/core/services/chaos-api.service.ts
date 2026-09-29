import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ChaosApiService {
  private http = inject(HttpClient);
  private baseUrl = '';

  public setScenario(scenarioName: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/chaos/scenario/${scenarioName}`, {});
  }

  public resetSimulation(): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/chaos/reset`, {});
  }

  public toggleMitigation(): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/mitigation/toggle`, {});
  }

  public getLiveTelemetry(): Observable<any> {
    return this.http.get(`${this.baseUrl}/telemetry/live`);
  }

  public getLoadConfig(): Observable<any> {
    return this.http.get(`${this.baseUrl}/admin/load/config`);
  }

  public setTps(tps: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/load/tps?tps=${encodeURIComponent(tps)}`, {});
  }

  public adjustTps(delta: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/load/adjust?delta=${encodeURIComponent(delta)}`, {});
  }

  public toggleStochastic(): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/load/toggle_stochastic`, {});
  }
}
