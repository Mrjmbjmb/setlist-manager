# Setlist Import API Examples

This document provides example JSON payloads that the import API expects.

## 1. **Full Import (Main Set + Encore)**
```json
{
  "mainSet": {
    "songs": [
      "Opening Song",
      "Second Song",
      "Third Song",
      "Fourth Song",
      "Closing Song"
    ],
    "duration": "01:23:45"
  },
  "encore": {
    "songs": [
      "Encore Song 1",
      "Encore Song 2"
    ],
    "duration": "00:15:30"
  }
}
```

## 2. **Main Set Only (Playing without Encore)**
```json
{
  "mainSet": {
    "songs": [
      "Song Title 1",
      "Song Title 2",
      "Song Title 3",
      "Song Title 4"
    ],
    "duration": "00:45:00"
  }
}
```

## 3. **Encore Only**
```json
{
  "encore": {
    "songs": [
      "Encore Song"
    ],
    "duration": "00:10:00"
  }
}
```

## 4. **Songs without Duration**
```json
{
  "mainSet": {
    "songs": [
      "Song 1",
      "Song 2",
      "Song 3"
    ]
  },
  "encore": {
    "songs": [
      "Encore 1"
    ]
  }
}
```

## Key Points:

1. **Duration Format**: Must be in `hh:mm:ss` format (e.g., `01:23:45` for 1 hour, 23 minutes, 45 seconds)
2. **Songs Array**: Must be an array of strings, one song title per element
3. **Partial Imports**: Either `mainSet` or `encore` or both can be included
4. **Duration is Optional**: The `duration` field is not required for either section
5. **Empty Sections**: You can omit sections you don't want to update

## Code Examples

### cURL Example:

```bash
# Full import
curl -X POST http://localhost:3001/api/import-setlist \
  -H "Content-Type: application/json" \
  -d '{
    "mainSet": {
      "songs": ["Song 1", "Song 2", "Song 3"],
      "duration": "00:30:00"
    },
    "encore": {
      "songs": ["Encore Song"],
      "duration": "00:05:00"
    }
  }'

# Main set only
curl -X POST http://localhost:3001/api/import-setlist \
  -H "Content-Type: application/json" \
  -d '{
    "mainSet": {
      "songs": ["Only Main Song 1", "Only Main Song 2"],
      "duration": "00:45:00"
    }
  }'
```

### Python Example:

```python
import requests
import json

# Full import example
payload = {
    "mainSet": {
        "songs": ["Song 1", "Song 2", "Song 3"],
        "duration": "00:45:00"
    },
    "encore": {
        "songs": ["Encore 1", "Encore 2"],
        "duration": "00:15:00"
    }
}

response = requests.post(
    "http://localhost:3001/api/import-setlist",
    headers={"Content-Type": "application/json"},
    json=payload
)

if response.status_code == 200:
    result = response.json()
    print(f"Success! Updated: {result['updated']}")
    print(f"Main set songs: {len(result['setlist']['mainSetSongs'])}")
    print(f"Encore songs: {len(result['setlist']['encoreSongs'])}")
else:
    print(f"Error: {response.json().get('error', 'Unknown error')}")
```

### JavaScript/Node.js Example:

```javascript
const axios = require('axios');

// Main set only import
const importSetlist = async () => {
  try {
    const response = await axios.post('http://localhost:3001/api/import-setlist', {
      mainSet: {
        songs: [
          "First Song",
          "Second Song",
          "Third Song",
          "Fourth Song"
        ],
        duration: "00:55:00"
      }
    });

    console.log('Import successful!', response.data);
  } catch (error) {
    if (error.response) {
      console.error('Import failed:', error.response.data.error);
    } else {
      console.error('Network error:', error.message);
    }
  }
};

importSetlist();
```

### PHP Example:

```php
<?php
$data = [
    'mainSet' => [
        'songs' => ['Song 1', 'Song 2', 'Song 3'],
        'duration' => '00:30:00'
    ],
    'encore' => [
        'songs' => ['Encore Song'],
        'duration' => '00:05:00'
    ]
];

$json = json_encode($data);

$ch = curl_init('http://localhost:3001/api/import-setlist');
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "POST");
curl_setopt($ch, CURLOPT_POSTFIELDS, $json);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Content-Length: ' . strlen($json)
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode == 200) {
    $result = json_decode($response, true);
    echo "Import successful!\n";
    echo "Updated: " . json_encode($result['updated']) . "\n";
} else {
    $error = json_decode($response, true);
    echo "Import failed: " . $error['error'] . "\n";
}
?>
```

## Response Format

### Success Response:
```json
{
  "success": true,
  "setlist": {
    "mainSetDuration": 2700,
    "encoreBreakDuration": 300,
    "encoreDuration": 900,
    "mainSetSongs": [
      {"title": "Song 1"},
      {"title": "Song 2"}
    ],
    "encoreSongs": [
      {"title": "Encore 1"}
    ],
    "encoreEnabled": true
  },
  "updated": {
    "mainSet": true,
    "encore": true
  }
}
```

### Error Response:
```json
{
  "success": false,
  "error": "mainSet.songs must be an array"
}
```

## Testing with the Provided Test Script

You can use the provided test script to verify the API works:

```bash
# Make sure the server is running on port 3001
node server/index.js

# In another terminal, run the test
node test-import.js
```