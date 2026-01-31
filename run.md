### Command example for mutemusic (NACC)
```python3 main.py   --subject 00   --session 01   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

### Test restarting from block

 

python soundtest.py

python main.py   --subject 03   --session 02 --blocks 11-20 --tasks mutemusic   --output output/sub03_AS_E2_B11-B20  --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri