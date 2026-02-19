### Command example for mutemusic (NACC)
```python3 main.py   --subject 00   --session 01   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

### Test restarting from block

 

python soundtest.py

python main.py   --subject 03   --session 10 --blocks 1-10 --tasks mutemusic   --output output/sub04_AO_E1_B1-B10  --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri