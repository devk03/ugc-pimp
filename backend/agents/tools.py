import json

## Tools for the Negotiate Agent
def get_current_weather(location):
    """
    This is our example tool with bs results.
    """
    print(f"--- Tool called: get_current_weather(location='{location}') ---")
    if "boston" in location.lower():
        return json.dumps({"location": "Boston", "temperature": "58", "unit": "Fahrenheit"})
    elif "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "22", "unit": "Celsius"})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})
    
    
## Tools for the Discovery Agent
# to be implemented