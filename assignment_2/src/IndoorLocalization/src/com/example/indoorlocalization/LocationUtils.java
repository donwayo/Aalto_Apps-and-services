package com.example.indoorlocalization;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import org.json.JSONObject;

import android.content.Context;
import android.content.res.AssetManager;
import android.util.Log;

public class LocationUtils {
	//private static final String[] ROOM_LIST = {"A112", "A118", "A124", "A130", "A136", "A141"};
	
	private Context mContext;
	private AssetManager mAssetManager;
	private List<DataModel> mModels;
	private String mBaseFolder;
	
	public LocationUtils(Context context, String baseFolder) {
		mContext = context;
		mAssetManager = mContext.getAssets();
		mModels = new ArrayList<DataModel>();
		mBaseFolder = baseFolder; 
	}
	
	//Prepare database model
	public void prepareData() {
		String [] roomList;
	    try {
	        roomList = mAssetManager.list(mBaseFolder);
	        for (String room : roomList) {
	        	String filename = mBaseFolder + "/" + room;
				DataModel model = DataModel.fromFile(mAssetManager, room, filename);
				mModels.add(model);
			}
	    } catch (Exception e) {
	    	e.printStackTrace();
	    }
	}
	
	public String findRoom(List<Map<String, Integer> > sampleList) {
		int[] countMatch = new int[mModels.size()];
		for (int i = 0; i < sampleList.size(); i++) {
			Map<String, Integer> sample = sampleList.get(i);
			
			double minDist = Double.MAX_VALUE;
			int minIndex = -1;
			Log.d("TAG", "Sample " + i);
			for (int j = 0; j < mModels.size(); j++) {
				double dist = mModels.get(j).distanceTo(sample);
				Log.d("TAG", "Distance to " + mModels.get(j).room + ": " + dist);
				if (dist < minDist) {
					minDist = dist;
					minIndex = j;
				}
			}
			if (minIndex != -1) {
				countMatch[minIndex]++;
			}
		}
		
		int maxCount = 0;
		int maxIndex = 0;
		for (int i = 0; i < mModels.size(); i++) {
			if (countMatch[i] > maxCount) {
				maxCount = countMatch[i];
				maxIndex = i;
			}
		}
		
		return mModels.get(maxIndex).room;
	}
	
	// Read test data from a file
	public List<Map<String, Integer> > readTestData(String room) {
		try {
			List<Map<String, Integer> > res = new ArrayList<Map<String, Integer> >();
			
			// wifi level data
			String filename = "test/" + room + ".csv";
			//String filename = room + ".csv";
			InputStream is = mAssetManager.open(filename);
			InputStreamReader isReader = new InputStreamReader(is);
		    BufferedReader br = new BufferedReader(isReader);
		    
		    String line;
		    Map<String, Integer> curSet = new HashMap<String, Integer>();
		    res.add(curSet);
		    while ((line = br.readLine()) != null) {
		    	if (line.trim().length() == 0) {
		    		curSet = new HashMap<String, Integer>();
		    		res.add(curSet);
		    		continue;
		    	}
		    	String[] fields = line.split(",");
		    	String ssid = fields[0];
		    	int levelVal = Integer.parseInt(fields[1]);
		    	curSet.put(ssid, levelVal);
		    }
		    
	        br.close();
	        
	        return res;
		} catch (Exception e) {
			e.printStackTrace();
		}
		return null;
	}
}



/**
 * Data model for a room
 */
class DataModel {
	String room;
	List<Map<String, Integer> > levelData;
	
	public DataModel(String _room) {
		room = _room;
		levelData = new ArrayList<Map<String, Integer> >();
	}
	
	// Calculate Euclid distance to another model containing a list wifi level and ssid 
	public double distanceTo(Map<String, Integer> sample) {
		// calculate the euclid distance to all models
		double res = Double.MAX_VALUE;
		
		for (Map<String, Integer> modelSet : levelData) {
			double countMatch = 0;
			double curDist = 0;
			for (String ssid : modelSet.keySet()) {
				if (!sample.containsKey(ssid)) {
					continue;
				}
				countMatch++;
				int sampleVal = sample.get(ssid);
				int modelVal = modelSet.get(ssid);
				curDist += Math.pow(modelVal - sampleVal, 2);
			}
			if (countMatch / sample.keySet().size() <= 0.7) {
				continue;
			}
			if (curDist < res) {
				res = curDist;
			}
		}
		
		res = Math.sqrt(res);// * (countMatch / sample.keySet().size());
		
		return res;
	}
	
	// read the model from a file
	public static DataModel fromFile(AssetManager assetManager, String _room, String filename) {
		try {
			// room name
			DataModel model = new DataModel(_room);
			
			// wifi level data
			InputStream is = assetManager.open(filename);
			InputStreamReader isReader = new InputStreamReader(is);
		    BufferedReader br = new BufferedReader(isReader);
		    
		    String line;
		    
		    Map<String, Integer> curSet = new HashMap<String, Integer>();
		    model.levelData.add(curSet);
		    while ((line = br.readLine()) != null) {
		    	if (line.length() == 0) {
		    		curSet = new HashMap<String, Integer>();
				    model.levelData.add(curSet);
		    		continue;
		    	}
		    	
		    	String[] fields = line.split(",");
		    	String ssid = fields[0];
		    	int levelVal = Integer.parseInt(fields[1]);
		    	
		    	curSet.put(ssid, levelVal);
		    }
		    
	        br.close();
	        
	        return model;
		} catch (Exception e) {
			e.printStackTrace();
		}
		return null;
	}
}

