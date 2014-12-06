package com.example.indoorlocalization;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

public class LocalLocation extends Fragment {
	private static final int TOTAL_ROUND = 1;
	
	private LocationUtils mGivenLocationUtils, mOurLocationUtils;
	private TextView mResultView;
	private boolean mIsRunning;
	private WifiManager mWifiManager;

	@Override
	public View onCreateView(LayoutInflater inflater, ViewGroup container,
			Bundle savedInstanceState) {
		View rootView = inflater.inflate(R.layout.activity_local_location,
				container, false);

		mGivenLocationUtils = new LocationUtils(getActivity(), "givendata");
		mGivenLocationUtils.prepareData();
		
		mOurLocationUtils = new LocationUtils(getActivity(), "ourdata");
		mOurLocationUtils.prepareData();
		
		mIsRunning = false;
		// init the wifi manager
		mWifiManager = (WifiManager) getActivity().getSystemService(Context.WIFI_SERVICE);
		
		mResultView = (TextView) rootView.findViewById(R.id.current_location);
		Button ourDetectionBtn = (Button) rootView.findViewById(R.id.detect_location_our);
		ourDetectionBtn.setOnClickListener(new OnClickListener() {
			@Override
			public void onClick(View arg0) {
				startDetectLocation(mOurLocationUtils);
			}
		});
		
		Button givenDetectionBtn = (Button) rootView.findViewById(R.id.detect_location_given);
		givenDetectionBtn.setOnClickListener(new OnClickListener() {
			@Override
			public void onClick(View arg0) {
				startDetectLocation(mGivenLocationUtils);
			}
		});
		
		return rootView;
	}
	
	@Override
	public void onDestroy() {
		super.onDestroy();
	}
	
	@Override
	public void onResume() {
		super.onResume();
		
	}
	
	private void startDetectLocation(LocationUtils locationUtils) {
		if (mIsRunning) {
			return;
		}
		mResultView.setText("Analyzing...");
		new DetectLocation(locationUtils).execute();
	}
	
	private void testGivenData() {
		List<Map<String, Integer> > a126data = mGivenLocationUtils.readTestData("A126");
		Log.d("TAG", "Result for A126: " + mGivenLocationUtils.findRoom(a126data));
		
		List<Map<String, Integer> > a150data = mGivenLocationUtils.readTestData("A150");
		Log.d("TAG", "Result for A150: " + mGivenLocationUtils.findRoom(a150data));
	}
	
	private class DetectLocation extends AsyncTask<Void, Void, Void> {
		private LocationUtils locationUtils;
		private List<Map<String, Integer> > sampleList;
		private int nRound;
		
		public DetectLocation(LocationUtils _locationUtils) {
			locationUtils = _locationUtils;
			sampleList = new ArrayList<Map<String, Integer> >();
			nRound = 0;
		}

		@Override
		protected Void doInBackground(Void... arg0) {
			mWifiManager.startScan();
			getActivity().registerReceiver(wifiScanReceiver, 
					new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
			mIsRunning = true;
			return null;
		}
		
		BroadcastReceiver wifiScanReceiver = new BroadcastReceiver() {
			@Override
			public void onReceive(Context c, Intent intent) {
				try {
					List<ScanResult> wifiList = mWifiManager.getScanResults();
					Map<String, Integer> wifiSet = new HashMap<String, Integer>();
					
					// print out the list
					for (int i = 0; i < wifiList.size(); i++) {
						ScanResult wifi = wifiList.get(i);
						wifiSet.put(wifi.BSSID, wifi.level);
					}
					
					sampleList.add(wifiSet);
					
					nRound++;
					if (nRound >= TOTAL_ROUND) {
						String res = locationUtils.findRoom(sampleList);
						mResultView.setText(res);
						mIsRunning = false;
					} else {
						mWifiManager.startScan(); 
					}
					
				} catch (Exception e) {
					e.printStackTrace();
				}
			}
		};
	} // Detect location

}
