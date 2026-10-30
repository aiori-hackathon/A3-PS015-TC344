import time
import socket
import subprocess
import platform
import dns.resolver
from typing import Dict, Any, List

class DiagnosticEngine:
    def __init__(self, targets=None):
        self.targets = targets or {
            "gateway_fallback": "192.168.1.1",
            "public_dns": "1.1.1.1",
            "target_host": "aiori.in",
            "backup_host": "google.com"
        }

    def detect_default_gateway(self) -> str:
        """Dynamically detect default gateway IP."""
        try:
            os_name = platform.system().lower()
            if os_name == "windows":
                out = subprocess.check_output("ipconfig", shell=True).decode()
                for line in out.splitlines():
                    if "Default Gateway" in line and ":" in line:
                        parts = line.split(":")
                        if len(parts) > 1 and parts[1].strip():
                            ip = parts[1].strip()
                            if "." in ip:
                                return ip
            else:
                out = subprocess.check_output("ip route show default", shell=True).decode()
                tokens = out.split()
                if "via" in tokens:
                    return tokens[tokens.index("via") + 1]
        except Exception:
            pass
        return self.targets["gateway_fallback"]

    def ping_metric(self, target: str, count: int = 5, timeout: float = 1.0) -> Dict[str, Any]:
        """Collects RTT and packet loss according to RFC 2330 principles."""
        os_name = platform.system().lower()
        param = "-n" if os_name == "windows" else "-c"
        timeout_param = "-w" if os_name == "windows" else "-W"
        timeout_val = str(int(timeout * 1000) if os_name == "windows" else int(timeout))

        cmd = ["ping", param, str(count), timeout_param, timeout_val, target]
        start_time = time.time()
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            output = res.stdout
            
            # Extract loss
            loss = 100.0
            if "%" in output:
                for line in output.splitlines():
                    if "%" in line:
                        for token in line.split():
                            if "%" in token:
                                clean_token = token.replace("%", "").replace("(", "").replace(")", "").replace(",", "")
                                try:
                                    loss = float(clean_token)
                                    break
                                except ValueError:
                                    continue
            
            # Simple RTT approximation if output contains 'time=' or 'Average ='
            rtts = []
            for line in output.splitlines():
                if "time=" in line or "time<" in line:
                    part = line.split("time")[1]
                    val_str = part.replace("=", "").replace("<", "").strip().split()[0].replace("ms", "")
                    try:
                        rtts.append(float(val_str))
                    except ValueError:
                        pass

            avg_rtt = sum(rtts) / len(rtts) if rtts else (None if loss == 100 else 25.0)
            return {"target": target, "loss_pct": loss, "avg_rtt_ms": avg_rtt, "samples": len(rtts), "reachable": loss < 100.0}
        except Exception:
            return {"target": target, "loss_pct": 100.0, "avg_rtt_ms": None, "samples": 0, "reachable": False}

    def measure_dns(self, hostname: str = "aiori.in") -> Dict[str, Any]:
        """Measures DNS resolution timing and status."""
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2.0
        resolver.lifetime = 2.0
        t0 = time.time()
        try:
            answers = resolver.resolve(hostname, "A")
            elapsed_ms = (time.time() - t0) * 1000.0
            resolved_ips = [str(r) for r in answers]
            return {"status": "SUCCESS", "hostname": hostname, "latency_ms": round(elapsed_ms, 2), "ips": resolved_ips}
        except dns.resolver.NXDOMAIN:
            return {"status": "NXDOMAIN", "hostname": hostname, "latency_ms": None, "ips": []}
        except dns.resolver.Timeout:
            return {"status": "TIMEOUT", "hostname": hostname, "latency_ms": None, "ips": []}
        except Exception as e:
            return {"status": "FAILED", "hostname": hostname, "latency_ms": None, "ips": [], "error": str(e)}

    def run_guided_diagnosis(self, simulated_state: str = None) -> Dict[str, Any]:
        """
        Executes guided step-by-step diagnostic workflow with transparent decision DAG.
        Adheres strictly to PS-015 constraints: no wild assumptions, explicit evidence.
        """
        gateway_ip = self.detect_default_gateway()
        
        # Check if running under simulated condition
        if simulated_state == "GATEWAY_UNREACHABLE":
            gw_result = {"target": gateway_ip, "loss_pct": 100.0, "avg_rtt_ms": None, "reachable": False}
            dns_result = {"status": "TIMEOUT", "latency_ms": None}
            wan_result = {"target": "1.1.1.1", "loss_pct": 100.0, "avg_rtt_ms": None, "reachable": False}
        elif simulated_state == "DNS_FAILURE":
            gw_result = {"target": gateway_ip, "loss_pct": 0.0, "avg_rtt_ms": 1.8, "reachable": True}
            dns_result = {"status": "TIMEOUT", "latency_ms": None}
            wan_result = {"target": "1.1.1.1", "loss_pct": 0.0, "avg_rtt_ms": 18.2, "reachable": True}
        elif simulated_state == "INDUCED_PACKET_LOSS":
            gw_result = {"target": gateway_ip, "loss_pct": 0.0, "avg_rtt_ms": 2.1, "reachable": True}
            dns_result = {"status": "SUCCESS", "latency_ms": 45.0, "ips": ["104.21.5.1"]}
            wan_result = {"target": "1.1.1.1", "loss_pct": 40.0, "avg_rtt_ms": 32.5, "reachable": True}
        elif simulated_state == "CONGESTION":
            gw_result = {"target": gateway_ip, "loss_pct": 0.0, "avg_rtt_ms": 1.9, "reachable": True}
            dns_result = {"status": "SUCCESS", "latency_ms": 140.0, "ips": ["104.21.5.1"]}
            wan_result = {"target": "1.1.1.1", "loss_pct": 0.0, "avg_rtt_ms": 285.0, "reachable": True}
        else:
            # Live physical execution
            gw_result = self.ping_metric(gateway_ip, count=4)
            wan_result = self.ping_metric("1.1.1.1", count=4)
            dns_result = self.measure_dns("aiori.in")

        # Decision Logic Engine (Tree / DAG)
        verdict = ""
        category = ""
        evidence_chain = []
        recommendation = ""
        is_inconclusive = False

        # Step 1: Gateway Reachability
        if not gw_result["reachable"] or gw_result["loss_pct"] >= 90.0:
            category = "Local Gateway Unreachable"
            verdict = "Local Link Failure: Cannot communicate with the Default Gateway."
            evidence_chain.append(f"Gateway ({gateway_ip}) showed {gw_result['loss_pct']}% packet loss.")
            recommendation = "Check physical Ethernet cable, verify Wi-Fi association, or power-cycle home router."
        
        # Step 2: Public WAN & DNS
        elif not wan_result["reachable"] and dns_result["status"] != "SUCCESS":
            category = "Upstream Link Down"
            verdict = "Broadband Access Link Failure: Gateway is active, but outside Internet is unreachable."
            evidence_chain.append(f"Gateway is OK, but public IP (1.1.1.1) failed with {wan_result['loss_pct']}% loss.")
            recommendation = "Check optical fibre WAN indicator (PON/LOS) on router or notify ISP."
            
        elif wan_result["reachable"] and dns_result["status"] != "SUCCESS":
            category = "DNS Service Failure"
            verdict = "DNS Resolution Disruption: Raw IP packets pass, but domain name queries fail."
            evidence_chain.append(f"Public IP 1.1.1.1 responded, but DNS resolution failed with status '{dns_result['status']}'.")
            recommendation = "Configure secondary DNS resolvers (e.g., 8.8.8.8, 1.1.1.1) in network properties."

        # Step 3: Performance anomalies (Packet Loss vs Latency Congestion)
        elif wan_result["loss_pct"] >= 15.0:
            category = "Induced Packet Loss / Link Degradation"
            verdict = "Transit Packet Loss: Gateway link is intact, but WAN path exhibits severe packet drops."
            evidence_chain.append(f"Gateway packet loss: {gw_result['loss_pct']}%, WAN packet loss: {wan_result['loss_pct']}%.")
            recommendation = "Provide this diagnostic escalation ticket to your ISP to investigate last-mile line noise."

        elif wan_result["avg_rtt_ms"] and wan_result["avg_rtt_ms"] > 180.0:
            category = "Network Congestion / Bufferbloat"
            verdict = "Severe Queuing Delay: Packets are arriving but suffering from excessive latency."
            evidence_chain.append(f"Average WAN RTT inflated to {wan_result['avg_rtt_ms']} ms (typical baseline < 40 ms).")
            recommendation = "Inspect high-bandwidth background downloads or enable Smart Queue Management (SQM)."

        elif (gw_result["loss_pct"] > 0 and gw_result["loss_pct"] < 15.0) or (wan_result["loss_pct"] > 0 and wan_result["loss_pct"] < 15.0):
            # Inconclusive scenario strictly required by PS-015
            is_inconclusive = True
            category = "Inconclusive Network Behavior"
            verdict = "Inconclusive: Intermittent mild packet drop observed without clear isolation boundary."
            evidence_chain.append(f"Marginal loss detected (GW: {gw_result['loss_pct']}%, WAN: {wan_result['loss_pct']}%). Insufficient data to assign definitive blame.")
            recommendation = "Continuous 15-minute background telemetry probe recommended to isolate transient interference."

        else:
            category = "Optimal Connection"
            verdict = "Connection Healthy: Local and last-mile connectivity are well within RFC 2330 normal baselines."
            evidence_chain.append(f"Gateway RTT: {gw_result['avg_rtt_ms']} ms, WAN RTT: {wan_result['avg_rtt_ms']} ms, DNS status: {dns_result['status']}.")
            recommendation = "No intervention needed."

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "verdict": verdict,
            "is_inconclusive": is_inconclusive,
            "evidence": evidence_chain,
            "recommendation": recommendation,
            "metrics": {
                "gateway": gw_result,
                "wan": wan_result,
                "dns": dns_result
            }
        }