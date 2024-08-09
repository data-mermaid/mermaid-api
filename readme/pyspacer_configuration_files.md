PySpacer Configuration Files
----------------------------

Location: `s3://mermaid-config/classification/`

## Versioning

Configuration file versions are stored in directories following the pattern of `vX` (examples: v1, v2, ..., vN).  Each version is a directory with the following structure:

```bash
[VERSION (pattern: vX)]
    ├── README.md: Description, notes, dates, etc of this version of the configuration files
    ├── efficientnet_weights.pt: EfficientNet weights.
    ├── classifier.pkl: Classifier model.
    └── valresult.json: Json output from the model that you need for visualization and calculating statistics
```

