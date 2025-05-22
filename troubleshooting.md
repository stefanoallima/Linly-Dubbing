# Troubleshooting Guide

## Table of Contents

- [yt-dlp Download Failures](#yt-dlp-download-failures)
- [Could not load library libcudnn_ops_infer.so.8](#could-not-load-library-libcudnn_ops_inferso8)

## yt-dlp Download Failures

Sometimes download failures may occur due to missing cookies. You can resolve this by generating a `cookies.txt` file and placing it in the program's root directory (you can generate it locally and then upload it to the server).

> Reference: https://github.com/yt-dlp/yt-dlp/wiki/FAQ

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt
```

## Could not load library libcudnn_ops_infer.so.8

This error usually occurs when the library file path cannot be found. It can be resolved by setting the `torch` path. Use the following command to set the `LD_LIBRARY_PATH` environment variable:

```bash
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/python3.8/site-packages/torch/lib
```
