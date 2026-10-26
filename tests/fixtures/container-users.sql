-- Imported only into the disposable MySQL container by container-isolation.sh.
INSERT INTO pc_forge.users(name,email,password_hash,role) VALUES
('CI Synthetic Customer','customer@fixture.test','$2y$10$swV2yCEl5AjzWKl/0qC/AOZ1/VaTsK2sLN949XWtXGWi.I5SB34KG','customer'),
('CI Synthetic Admin','admin@fixture.test','$2y$10$d8QqWmP5XQseorIzJO1XV.Y.OIYQprq1.Js9ODZ9ImLJCkMufiZXu','admin');
