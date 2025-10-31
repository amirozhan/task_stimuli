### Command example for mutemusic (NACC)
```python3 main.py   --subject 00   --session 01   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

### Test restarting from block
```python main.py   --subject 00   --session 01 --blocks 3   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

```python main.py   --subject 00   --session 01 --blocks X-20   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```