### Command example for mutemusic (NACC)
```python3 main.py   --subject 00   --session 01   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

### Test restarting from block





python soundtest.py
python main.py   --subject 01   --session 01 --blocks 9   --tasks mutemusic   --output output/SH_test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri 

python main.py   --subject 01   --session 01 --blocks 17-20   --tasks mutemusic   --output output/SH_test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri 

python main.py   --subject 01   --session 02 --blocks 1-10   --tasks mutemusic   --output output/SH_test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri 