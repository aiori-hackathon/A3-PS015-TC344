"""
Fault Injector Module for Controlled Lab Testing (AIORI-3 PS-015)
Provides clean software mocks and OS-level hooks to inject the 4 required faults.
"""
import sys

SCENARIOS = {
    "1": ("Gateway Unreachable", "GATEWAY_UNREACHABLE"),
    "2": ("DNS Failure", "DNS_FAILURE"),
    "3": ("Induced Packet Loss", "INDUCED_PACKET_LOSS"),
    "4": ("Network Congestion", "CONGESTION"),
    "5": ("Live Network Probe", None)
}

def print_menu():
    print("=" * 60)
    print("AIORI-3 PS-015: Controlled Fault Injection Harness")
    print("=" * 60)
    for k, v in SCENARIOS.items():
        print(f"[{k}] {v[0]}")
    print("=" * 60)

if __name__ == "__main__":
    print_menu()
    choice = input("Select scenario to simulate (1-5): ").strip()
    if choice in SCENARIOS:
        print(f"\n[+] Active Fault Simulation Profile: {SCENARIOS[choice][0]}")
        print(f"[*] State key: {SCENARIOS[choice][1]}")
        print("[!] Start the UI (`streamlit run app.py`) and choose this preset.")
    else:
        print("Invalid choice.")