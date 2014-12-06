package com.example.indoorlocalization;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.support.v4.app.Fragment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

public class CollectData extends Fragment {
	private static final int TOTAL_ROUND = 15;
	
	private EditText mRoomView;
	private WifiManager mWifiManager;

	@Override
	public View onCreateView(LayoutInflater inflater, ViewGroup container,
			Bundle savedInstanceState) {
		View rootView = inflater.inflate(R.layout.activity_collect_data,
				container, false);
		// init the wifi manager
		mWifiManager = (WifiManager) getActivity().getSystemService(Context.WIFI_SERVICE);
		
		mRoomView = (EditText) rootView.findViewById(R.id.room_id);
		Button startBtn = (Button) rootView.findViewById(R.id.start_collect);
		
		startBtn.setOnClickListener(new OnClickListener() {
			@Override
			public void onClick(View arg0) {
				// close keyboard
				InputMethodManager imm = (InputMethodManager) getActivity().getSystemService(
					      Context.INPUT_METHOD_SERVICE);
				imm.hideSoftInputFromWindow(mRoomView.getWindowToken(), 0);
					
				// check room
				String room = mRoomView.getText().toString();
				if (room.trim().length() == 0) {
					Toast.makeText(getActivity(), "Please enter the room number", 
									Toast.LENGTH_LONG).show();
					return;
				}
				if (mWifiManager.isWifiEnabled() == false) {
					Toast.makeText(getActivity(), "Wifi is disabled", 
							Toast.LENGTH_LONG).show();
				}
				// start scan
				new ScanWifi(room).execute();
			}
		});
		
		return rootView;
	}
	
	private class ScanWifi extends AsyncTask<Void, Void, Void> {
		private String room;
		private int nRound;
		private BufferedWriter output;
		
		public ScanWifi(String _room) {
			room = _room;
			nRound = 1;
			// open output file
			try {
				File sdCard = Environment.getExternalStorageDirectory();
				File dir = new File (sdCard.getAbsolutePath() + "/wifidata");
				if (!dir.exists()) {
					dir.mkdirs();
				}
				
				DateFormat dateFormat = new SimpleDateFormat("yyyyMMdd_HHmmss");
				Date date = new Date();
				String filename = room + "_" + dateFormat.format(date) + ".csv";
				File file = new File(dir, filename);
				FileWriter fw = new FileWriter(file.getAbsoluteFile());
				output = new BufferedWriter(fw);
			} catch (Exception e) {
				e.printStackTrace();
			}
		}

		@Override
		protected Void doInBackground(Void... arg0) {
			mWifiManager.startScan();
			getActivity().registerReceiver(wifiScanReceiver, 
					new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
			return null;
		}
		
		private void displayStatus() {
			Toast.makeText(getActivity(), "Finish scanning round " + nRound + "...", 
							Toast.LENGTH_SHORT).show();
		}
		
		BroadcastReceiver wifiScanReceiver = new BroadcastReceiver() {
			@Override
			public void onReceive(Context c, Intent intent) {
				displayStatus();
				
				try {
					List<ScanResult> wifiList = mWifiManager.getScanResults();
					
					// print out the list
					for (int i = 0; i < wifiList.size(); i++) {
						ScanResult wifi = wifiList.get(i);
						output.write(wifi.BSSID + "," + wifi.level + "\n");
					}
					
					if (nRound >= TOTAL_ROUND) {
						getActivity().unregisterReceiver(this);
						output.close();
					} else {
						output.write("\n");
						// scan again
						Handler handler = new Handler(); 
					    handler.postDelayed(new Runnable() { 
					    	public void run() { 
					        	nRound++;
								mWifiManager.startScan(); 
					        } 
					    }, 5000); 
					}
				} catch (Exception e) {
					e.printStackTrace();
				}
			}
		};
	} // ScanWifi

}