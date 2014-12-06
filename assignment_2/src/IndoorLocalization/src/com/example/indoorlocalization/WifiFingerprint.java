package com.example.indoorlocalization;

import java.util.Collections;
import java.util.Comparator;
import java.util.List;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.IntentFilter;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.Toast;
import android.content.Intent;

public class WifiFingerprint extends Fragment {

	WifiManager mWifiManager;
	TextView mWifiListView;

	@Override
	public View onCreateView(LayoutInflater inflater, ViewGroup container,
			Bundle savedInstanceState) {
		View rootView = inflater.inflate(R.layout.activity_wifi_fingerprint,
				container, false);

		mWifiListView = (TextView) rootView.findViewById(R.id.wifi_list);

		mWifiManager = (WifiManager) getActivity().getSystemService(Context.WIFI_SERVICE);
		if (mWifiManager.isWifiEnabled() == false) {
			mWifiListView.setText("Wifi is disabled");
		} else {
			scanWifi();
		}
		return rootView;
	}

	private void scanWifi() {
		mWifiManager.startScan();
		mWifiListView.setText("Scanning...");
		getActivity().registerReceiver(new BroadcastReceiver() {
			@Override
			public void onReceive(Context c, Intent intent) {
				if (intent.getAction() == WifiManager.SCAN_RESULTS_AVAILABLE_ACTION) {
					List<ScanResult> wifiList = mWifiManager.getScanResults();
					// sort the list by name
					Collections.sort(wifiList, new Comparator<ScanResult>(){
					     public int compare(ScanResult o1, ScanResult o2){
					    	 return o1.SSID.compareTo(o2.SSID);
					     }
					});
					
					// print out the list;
					String text = "";
					for (int i = 0; i < wifiList.size(); i++) {
						ScanResult wifi = wifiList.get(i);
						text += (i+1) + ". " + wifiToString(wifi) + "\r\n";
					}
					//Log.d("TAG", text);
					mWifiListView.setText(text);
		        }
			}
		}, new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
	}
	
	private String wifiToString(ScanResult wifi) {
		if (wifi == null) {
			return "";
		}
		String res = "";
		res += "SSID: " + wifi.SSID + "\r\n";
		res += "BSSID: " + wifi.BSSID + "\r\n";
		//res += "Capabilities: " + wifi.capabilities + "\r\n";
		res += "Level: " + wifi.level + "\r\n";
		return res;
	}

}
