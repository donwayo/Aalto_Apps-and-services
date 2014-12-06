package com.example.indoorlocalization;

import java.util.List;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView.FindListener;
import android.widget.TextView;

public class Sensors extends Fragment {
	
	private SensorManager mSensorManager;
	private TextView mSensorsView;
	private List<Sensor> mSensorsList;

	@Override
	public View onCreateView(LayoutInflater inflater, ViewGroup container,
			Bundle savedInstanceState) {
		View rootView = inflater.inflate(R.layout.activity_sensors, container,
				false);
		
		// Get the SensorManager 
	    mSensorManager= (SensorManager) getActivity().getSystemService(Context.SENSOR_SERVICE);

	    // List of Sensors Available
	    mSensorsList = mSensorManager.getSensorList(Sensor.TYPE_ALL);

	    // Print how may Sensors are there
	    mSensorsView = (TextView) rootView.findViewById(R.id.sensors_list);

	    // Print each Sensor available using sSensList as the String to be printed
	    String text = "";
	    for (int i = 0; i < mSensorsList.size(); i++){
	    	text += (i+1) + ". " + mSensorsList.get(i).getName() + "\r\n";
	    }
	    
	    mSensorsView.setText(text);

		return rootView;
	}
}
