use std::env;

use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use ratatui_image::{picker::Picker, protocol::StatefulProtocol, StatefulImage};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: rvimg <image-path>");
        std::process::exit(1);
    }
    let path = &args[1];

    // Detect terminal protocol + font size (must run before init)
    let picker = Picker::from_query_stdio().unwrap_or_else(|_| Picker::halfblocks());

    // Load image
    let dyn_img = image::ImageReader::open(path)?.decode()?;
    let mut image_state = picker.new_resize_protocol(dyn_img);

    let mut terminal = ratatui::init();
    let result = run(&mut terminal, &mut image_state);
    ratatui::restore();

    result
}

fn run(
    terminal: &mut ratatui::DefaultTerminal,
    image_state: &mut StatefulProtocol,
) -> Result<(), Box<dyn std::error::Error>> {
    loop {
        terminal.draw(|frame| {
            let image = StatefulImage::default();
            frame.render_stateful_widget(image, frame.area(), image_state);
        })?;

        if event::poll(std::time::Duration::from_millis(100))? {
            match event::read()? {
                Event::Key(key) if key.kind == KeyEventKind::Press => match key.code {
                    KeyCode::Char('q') | KeyCode::Esc => return Ok(()),
                    _ => {}
                },
                _ => {}
            }
        }
    }
}
